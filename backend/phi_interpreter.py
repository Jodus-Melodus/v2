from backend.values import *
from frontend.astNodes import *
from frontend.errors import *
from backend.phi_environment import environment, createGlobalEnvironment

booleanTable = {
    'T':True,
    'F':False
}

class Interpreter:
    def __init__(self) -> None:
        pass

    def __str__(self) -> str:
        return 'Interpreter'

    def checkCondition(self, left: RuntimeValue, operand: str, right: RuntimeValue) -> bool:
        res = False
        if isinstance(right, nullValue):
            if isinstance(left, (realValue, integerValue)):
                if left.value != 0:
                    res = booleanValue('T')
                else:
                    res = booleanValue('F')
            elif isinstance(left, booleanValue):
                res = True if left.value == 'T' else False
            elif isinstance(left, stringValue):
                res = left.value != ''
        else:
            if isinstance(left, (realValue, integerValue)) and isinstance(right, (realValue, integerValue)):
                match operand:
                    case '==':
                        res = left.value == right.value
                    case '>':
                        res = left.value > right.value
                    case '<':
                        res = left.value < right.value
                    case '>=':
                        res = left.value >= right.value
                    case '<=':
                        res = left.value <= right.value
                    case '!=':
                        res = left.value != right.value
            elif isinstance(left, booleanValue) and isinstance(right, booleanValue):
                match operand:
                    case '&':
                        res = booleanTable[left.value] and booleanTable[right.value]
                    case '|':
                        res = booleanTable[left.value] or booleanTable[right.value]
                    case '!=':
                        res = booleanTable[left.value] != booleanTable[right.value]
            elif isinstance(left, stringValue) and isinstance(right, stringValue):
                match operand:
                    case '==':
                        res = left.value == right.value
                    case '!=':
                        res = left.value != right.value
        return res

    def evaluateProgram(self, program: programNode, env: environment) -> nullValue | integerValue | objectValue | arrayValue | stringValue | bool | None:
        lastEvaluated = nullValue()

        for statement in program.body:
            lastEvaluated = self.evaluate(statement, env)
            if isinstance(lastEvaluated, error):
                return lastEvaluated

        return lastEvaluated

    def evaluateBinaryExpression(self, binaryOperation:binaryExpressionNode, env: environment) -> integerValue | nullValue:
        left = self.evaluate(binaryOperation.left, env)
        if isinstance(left, error):
            return left
        right = self.evaluate(binaryOperation.right, env)
        if isinstance(right, error):
            return right

        if isinstance(left, (realValue, integerValue)) and isinstance(right, (realValue, integerValue)):
            return self.evaluateNumericBinaryExpression(left, right, binaryOperation.operand)
        elif isinstance(left, stringValue) and isinstance(right, (stringValue, (realValue, integerValue))):
            return self.evaluateStringBinaryExpression(left, right, binaryOperation.operand)
        
        elif isinstance(left, arrayValue):
            return self.evaluateArrayAppendBinaryExpression(left, right, binaryOperation.operand)
        else:
            return syntaxError(self, "Cannot preform this operation.")
        
    def evaluateArrayAppendBinaryExpression(self, left:arrayValue, right, operand:str) -> arrayValue:
        match operand:
            case '+':
                index = len(left.items)
                left.items[index] = right
                return arrayValue(left.items)
            case _:
                return syntaxError(self, "Cannot preform this operation on arrays.")
        
    def evaluateObjectBinaryExpression(self, left:objectValue, right:objectValue, operand:str) -> objectValue:
        match operand:
            case '+':
                return objectValue(left.properties.update(right.properties))
            case _:
                return syntaxError(self, "Cannot preform this operation on objects.")

    def evaluateArrayBinaryExpression(self, left:arrayValue, right:arrayValue, operand:str) -> arrayValue:
        match operand:
            case '+':
                return arrayValue(left.items + right.items)
            case _:
                return syntaxError(self, "Cannot preform this operation on arrays.")

    def evaluateStringBinaryExpression(self, left:stringValue, right:stringValue|integerValue|realValue, operand:str) -> stringValue:
        match operand:
            case '+':
                return stringValue(left.value + right.value)
            case _:
                return syntaxError(self, "Cannot preform this operation on strings.")

    def evaluateNumericBinaryExpression(self, left:integerValue|realValue, right:integerValue|realValue, operand:str) -> realValue:
        match operand:
            case '+':
                return realValue(left.value + right.value)
            case '-':
                return realValue(left.value - right.value)
            case '*':
                return realValue(left.value * right.value)
            case '/':
                if right.value != 0:
                    return realValue(left.value / right.value)
                else:
                    return zeroDivisionError(self)
            case '^':
                return realValue(left.value ** right.value)
            case '%':
                if right.value != 0:
                    return realValue(left.value % right.value)
                else:
                    return zeroDivisionError(self)
            case '//':
                if right.value != 0:
                    return realValue(left.value // right.value)
                else:
                    return zeroDivisionError(self)
            case _:
                return syntaxError(self, "Cannot preform this operation on numbers")

# --------------------------------------------------------------------------------------------------------------------------------

    def evaluateIdentifierExpression(self, identifier: identifierNode, env: environment) -> None:
        return env.lookup(identifier)

    def evaluateAssignmentExpression(self, assignmentExpression: assignmentExpressionNode, env: environment) -> None:
        if isinstance(assignmentExpression.assigne, identifierNode):
            varName = assignmentExpression.assigne.symbol
            return env.assignVariable(varName, self.evaluate(assignmentExpression.value, env))
        elif isinstance(assignmentExpression.assigne, memberExpressionNode):
            member: memberExpressionNode = assignmentExpression.assigne
            varName = member.object
            prop = member.property.symbol
            currentValue: dict = env.lookup(varName)
            currentValue.properties[prop] = self.evaluate(
                assignmentExpression.value, env)
            return env.assignVariable(varName, currentValue)
        else:
            return syntaxError(self, 'Expected an identifier.', assignmentExpression.assigne.column, assignmentExpression.assigne.line)

    def evaluateVariableDeclarationExpression(self, declaration: variableDeclarationExpressionNode, env: environment) -> None:
        value = self.evaluate(declaration.value, env)
        if isinstance(value, error):
            return value
        return env.declareVariable(declaration.identifier, value, declaration.constant)

    def evaluateFunctionDeclaration(self, declaration: functionDeclarationExpressionNode, env: environment) -> None:
        fn = function(declaration.name, declaration.parameters, env, declaration.body)
        return env.declareVariable(declaration.name, fn)

    def evaluateObjectExpression(self, object: objectLiteralNode, env: environment) -> objectValue:
        properties = {}

        for prop in object.properties:
            a = self.evaluate(prop.value, env)
            if isinstance(a, error):
                return a
            properties[prop.key] = a
        obj = objectValue(properties)
        return obj

    def evaluateArrayExpression(self, array: arrayLiteralNode, env: environment) -> arrayValue:
        items = {}

        for item in array.items:
            items[item.index] = self.evaluate(item.value, env)
        arr = arrayValue(items)
        return arr

    def evaluateCallExpression(self, callExpr: callExpression, env: environment) -> nullValue | integerValue | objectValue | arrayValue | stringValue | bool | None:
        args = []
        for arg in callExpr.arguments:
            a = self.evaluate(arg, env)
            if isinstance(a, error):
                return a
            args.append(a)
        fn: nativeFunction | function = self.evaluate(callExpr.caller, env)
        if isinstance(fn, error):
            return fn

        if isinstance(fn, nativeFunction):
            result = fn.call(args, env)
            return result
        elif isinstance(fn, function):
            scope = createGlobalEnvironment(fn.declarationEnvironment)
            scope.declareVariable(fn.name, scope.parent.lookup(identifierNode(fn.name, 0, 0)))

            if len(fn.parameters) == len(args):
                for i in range(len(fn.parameters)):
                    scope.declareVariable(fn.parameters[i].symbol, args[i])
            else:
                if len(fn.parameters) > 0:
                    column = fn.parameters[-1].column
                    line = fn.parameters[-1].line
                else:
                    column = 0
                    line = 0
                return syntaxError(self, f'Insufficient arguments provided. Expected {len(fn.parameters)}, but received {len(args)}', column, line)

            result = nullValue()
            for statement in fn.body:
                result = self.evaluate(statement, scope)
                if isinstance(result, error):
                    return result
                if isinstance(statement, returnNode):
                    return result
        else:
            return syntaxError(self, f"'{fn}' is not a function")

    def evaluateMemberExpression(self, member: memberExpressionNode, env: environment) -> None:
        obj:objectValue = env.lookup(member.object)

        if isinstance(obj, objectValue):
            if isinstance(member.property, identifierNode):
                if member.property.symbol not in obj.properties:
                    return keyError(self, member.property.symbol, member.object.symbol, member.property.column, member.property.line)

                elif isinstance(member.property, stringValue):
                    return obj.properties[member.property.value]
                return obj.properties[member.property.symbol]
        elif isinstance(obj, (arrayValue, stringValue)):
            if isinstance(member.property, integerLiteralNode):
                if member.property.value not in obj.items:
                    return keyError(self, member.property.value, member.object.symbol, member.property.column, member.property.line)

                elif isinstance(member.property, integerLiteralNode):
                    return obj.items[member.property.value]
            elif isinstance(member.property, identifierNode):
                if member.property.symbol in obj.methods:
                    return obj.methods[member.property.symbol]
                else:
                    value = self.evaluate(member.property, env).value
                    if value in obj.items:
                        return obj.items[value]
                    else:
                        return syntaxError(self, f"'{member.property.symbol}' is not a valid method or property.")
            else:
                return syntaxError(self, f"'{member.property.symbol}' is not valid.")
        else:
            return keyError(self, member.property, member.object.symbol, member.property.column, member.property.line)

    def evaluateIfStatement(self, ifStatement: ifStatementNode, env: environment) -> None:
        left: RuntimeValue = self.evaluate(ifStatement.conditionLeft, env)
        if isinstance(left, error):
            return left
        if not isinstance(ifStatement.conditionRight, nullValue):
            right: RuntimeValue = self.evaluate(ifStatement.conditionRight, env)
            if isinstance(right, error):
                return right
        else:
            right = nullValue()

        res = False
        res = self.checkCondition(left, ifStatement.operand, right)
        if res:
            result = nullValue()
            for statement in ifStatement.body:
                result = self.evaluate(statement, env)
                if isinstance(result, error):
                    return result
                if isinstance(statement, returnNode):
                    return result
        else:
            if ifStatement.elseBody != []:
                result = nullValue()
                for statement in ifStatement.elseBody:
                    result = self.evaluate(statement, env)
                    if isinstance(result, error):
                        return result
                    if isinstance(statement, returnNode):
                        return result
        return nullValue()

    def evaluateWhileStatement(self, whileStatement: whileStatementNode, env: environment) -> bool:
        while True:
            left: RuntimeValue = self.evaluate(
                whileStatement.conditionLeft, env)
            if isinstance(left, error):
                return left
            if not isinstance(whileStatement.conditionRight, nullValue):
                right: RuntimeValue = self.evaluate(
                    whileStatement.conditionRight, env)
                if isinstance(right, error):
                    return right
            else:
                right = nullValue()

            res = False
            res = self.checkCondition(left, whileStatement.operand, right)
            if res:
                result = nullValue()
                for statement in whileStatement.body:
                    if isinstance(statement, returnNode):
                        return result
                    result = self.evaluate(statement, env)
                    if isinstance(result, error):
                        return result
            else:
                if whileStatement.elseBody != []:
                    result = nullValue()
                    for statement in whileStatement.elseBody:
                        result = self.evaluate(statement, env)
                        if isinstance(result, error):
                            return result
                        if isinstance(statement, returnNode):
                            return result
                break
        return nullValue()

    def evaluateDoWhileStatement(self, doWhile: doWhileStatementNode, env: environment) -> None:
        res = True
        while True:
            if res:
                result = nullValue()
                for statement in doWhile.body:
                    if isinstance(statement, returnNode):
                        return result
                    result = self.evaluate(statement, env)
                    if isinstance(result, error):
                        return result

                left: RuntimeValue = self.evaluate(doWhile.conditionLeft, env)
                if isinstance(left, error):
                    return result
                if not isinstance(doWhile.conditionRight, nullValue):
                    right: RuntimeValue = self.evaluate(
                        doWhile.conditionRight, env)
                    if isinstance(right, error):
                        return result
                else:
                    right = nullValue()

                res = self.checkCondition(left, doWhile.operand, right)
            else:
                break
        return nullValue()

    def evaluateReturnExpression(self, returnExpression: returnNode, env: environment):
        return self.evaluate(returnExpression.value, env)

    def evaluateAssignmentBinaryExpression(self, expr: assignmentBinaryExpressionNode, env: environment) -> None:
        currentValue = env.lookup(expr.assigne)
        newValue = self.evaluateBinaryExpression(binaryExpressionNode(
            realLiteralNode(currentValue.value, 0, 0), expr.operand[0], expr.value), env)
        return self.evaluateAssignmentExpression(assignmentExpressionNode(expr.assigne, realLiteralNode(newValue.value, 0, 0)), env)

    def evaluate(self, astNode, env: environment) -> nullValue | integerValue | objectValue | arrayValue | stringValue | None:
        if isinstance(astNode, (str, float, int)):
            return astNode
        match astNode.kind:
            case 'program':
                return self.evaluateProgram(astNode, env)
            case 'binaryExpression':
                return self.evaluateBinaryExpression(astNode, env)
            case 'identifier':
                return self.evaluateIdentifierExpression(astNode, env)
            case 'assignmentExpression':
                return self.evaluateAssignmentExpression(astNode, env)
            case 'variableDeclarationExpression':
                return self.evaluateVariableDeclarationExpression(astNode, env)
            case 'functionDeclaration':
                return self.evaluateFunctionDeclaration(astNode, env)
            case 'objectLiteral':
                return self.evaluateObjectExpression(astNode, env)
            case 'callExpression':
                return self.evaluateCallExpression(astNode, env)
            case 'memberExpression':
                return self.evaluateMemberExpression(astNode, env)
            case 'ifStatement':
                return self.evaluateIfStatement(astNode, env)
            case 'whileStatement':
                return self.evaluateWhileStatement(astNode, env)
            case 'doWhileStatement':
                return self.evaluateDoWhileStatement(astNode, env)
            case 'arrayLiteral':
                return self.evaluateArrayExpression(astNode, env)
            case 'returnExpression':
                return self.evaluateReturnExpression(astNode, env)
            case 'assignmentBinaryExpression':
                return self.evaluateAssignmentBinaryExpression(astNode, env)

            case 'integerLiteral':
                return integerValue(astNode.value)
            case 'realLiteral':
                return realValue(astNode.value)
            case 'nullLiteral':
                return nullValue()
            case 'stringLiteral':
                return stringValue(astNode.value)
            case _:
                return notImplementedError(self, astNode)
